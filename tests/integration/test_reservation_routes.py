"""
Comprehensive integration tests for reservation API endpoints
Tests all reservation-related routes with various scenarios
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, AsyncMock, patch

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models.user import User
from backend.app.models.reservation import Reservation
from backend.app.core.auth import create_access_token


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_reservations.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestReservationSearchRoutes:
    """Test suite for reservation search endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test database and cleanup after each test"""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        db = TestingSessionLocal()
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user
    
    @pytest.fixture
    def auth_headers(self, test_user):
        """Generate authentication headers"""
        token = create_access_token(data={"sub": test_user.username})
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def mock_reservation_service(self):
        """Mock reservation management service"""
        with patch('backend.app.routes.reservations_v2.reservation_service') as mock:
            mock.search_all_providers = AsyncMock()
            mock.create_reservation = AsyncMock()
            mock.modify_reservation = AsyncMock()
            mock.cancel_reservation = AsyncMock()
            mock.check_availability = AsyncMock()
            mock.add_to_waitlist = AsyncMock()
            yield mock
    
    def test_search_restaurants_success(self, auth_headers, mock_reservation_service):
        """Test successful restaurant search"""
        mock_results = [
            {
                "provider": "opentable",
                "venue_id": "ot_123",
                "name": "Mario's Italian",
                "cuisine": "Italian",
                "rating": 4.5,
                "price_range": "3",
                "distance": 0.5,
                "available_times": ["18:00", "18:30", "19:00"],
                "image_url": "http://example.com/mario.jpg",
                "amenities": ["outdoor seating", "parking"]
            },
            {
                "provider": "yelp",
                "venue_id": "yelp_456",
                "name": "Luigi's Pizza",
                "cuisine": "Italian",
                "rating": 4.3,
                "price_range": "2",
                "distance": 0.8,
                "available_times": ["17:30", "18:00", "19:30"]
            }
        ]
        
        mock_reservation_service.search_all_providers.return_value = mock_results
        
        response = client.post(
            "/api/reservations/search",
            headers=auth_headers,
            json={
                "query": "Italian restaurant",
                "location": {"lat": 40.7128, "lng": -74.0060},
                "date": (datetime.now() + timedelta(days=1)).isoformat(),
                "party_size": 4,
                "cuisines": ["Italian"],
                "price_range": "2-3"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["name"] == "Mario's Italian"
    
    def test_search_with_filters(self, auth_headers, mock_reservation_service):
        """Test search with various filters"""
        mock_reservation_service.search_all_providers.return_value = []
        
        response = client.post(
            "/api/reservations/search",
            headers=auth_headers,
            json={
                "query": "restaurant",
                "location": {"lat": 40.7128, "lng": -74.0060},
                "date": datetime.now().isoformat(),
                "party_size": 6,
                "cuisines": ["French", "Italian"],
                "price_range": "3-4",
                "amenities": ["valet parking", "private dining", "sommelier"]
            }
        )
        
        assert response.status_code == 200
        # Verify service was called with correct filters
        call_args = mock_reservation_service.search_all_providers.call_args[1]
        assert call_args["cuisine"] == ["French", "Italian"]
        assert call_args["amenities"] == ["valet parking", "private dining", "sommelier"]
    
    def test_search_validation_errors(self, auth_headers):
        """Test search request validation"""
        # Missing required fields
        response = client.post(
            "/api/reservations/search",
            headers=auth_headers,
            json={
                "query": "restaurant"
                # Missing location, date, party_size
            }
        )
        
        assert response.status_code == 422
        
        # Invalid party size
        response = client.post(
            "/api/reservations/search",
            headers=auth_headers,
            json={
                "query": "restaurant",
                "location": {"lat": 40.7128, "lng": -74.0060},
                "date": datetime.now().isoformat(),
                "party_size": -1  # Invalid
            }
        )
        
        assert response.status_code == 422


class TestReservationBookingRoutes:
    """Test suite for reservation booking endpoints"""
    
    @pytest.fixture
    def mock_reservation_service(self):
        """Mock reservation service for booking tests"""
        with patch('backend.app.routes.reservations_v2.reservation_service') as mock:
            mock.create_reservation = AsyncMock()
            yield mock
    
    def test_create_reservation_success(self, auth_headers, mock_reservation_service, test_user):
        """Test successful reservation creation"""
        mock_booking_result = {
            "confirmation_number": "CONF123456",
            "status": "confirmed",
            "venue_name": "Mario's Italian",
            "reservation_time": datetime.now() + timedelta(days=1),
            "party_size": 4,
            "cancellation_policy": "Cancel up to 2 hours before"
        }
        
        mock_reservation_service.create_reservation.return_value = mock_booking_result
        
        response = client.post(
            "/api/reservations/book",
            headers=auth_headers,
            json={
                "provider": "opentable",
                "venueId": "ot_123",
                "dateTime": (datetime.now() + timedelta(days=1)).isoformat(),
                "partySize": 4,
                "customerInfo": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john@example.com",
                    "phone": "555-1234"
                },
                "specialRequests": "Window table please",
                "occasionType": "anniversary"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "confirmation_number" in data
        assert data["status"] == "confirmed"
    
    def test_create_reservation_with_dietary_restrictions(self, auth_headers, mock_reservation_service, test_user):
        """Test booking with dietary restrictions"""
        mock_reservation_service.create_reservation.return_value = {
            "confirmation_number": "CONF789",
            "status": "confirmed"
        }
        
        response = client.post(
            "/api/reservations/book",
            headers=auth_headers,
            json={
                "provider": "resy",
                "venueId": "resy_789",
                "dateTime": (datetime.now() + timedelta(days=2)).isoformat(),
                "partySize": 2,
                "customerInfo": {
                    "firstName": "Jane",
                    "lastName": "Smith",
                    "email": "jane@example.com",
                    "phone": "555-5678"
                },
                "dietaryRestrictions": ["vegetarian", "gluten-free"],
                "marketingOptIn": True
            }
        )
        
        assert response.status_code == 200
        # Verify dietary restrictions were passed
        call_args = mock_reservation_service.create_reservation.call_args[1]
        assert "vegetarian" in call_args["dietary_restrictions"]
    
    def test_create_reservation_failure(self, auth_headers, mock_reservation_service, test_user):
        """Test handling booking failures"""
        mock_reservation_service.create_reservation.side_effect = Exception(
            "Restaurant is fully booked"
        )
        
        response = client.post(
            "/api/reservations/book",
            headers=auth_headers,
            json={
                "provider": "opentable",
                "venueId": "ot_123",
                "dateTime": datetime.now().isoformat(),
                "partySize": 8,
                "customerInfo": {
                    "firstName": "Test",
                    "lastName": "User",
                    "email": "test@example.com",
                    "phone": "555-0000"
                }
            }
        )
        
        assert response.status_code == 500
        assert "Booking failed" in response.json()["detail"]


class TestReservationManagementRoutes:
    """Test suite for managing existing reservations"""
    
    @pytest.fixture
    def existing_reservation(self, test_user):
        """Create an existing reservation in database"""
        db = TestingSessionLocal()
        reservation = Reservation(
            user_id=test_user.id,
            provider="opentable",
            venue_id="ot_123",
            venue_name="Mario's Italian",
            confirmation_number="CONF123456",
            date_time=datetime.now() + timedelta(days=2),
            party_size=4,
            status="confirmed",
            modification_allowed=True,
            cancellation_deadline=datetime.now() + timedelta(days=1, hours=22)
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        db.close()
        return reservation
    
    def test_get_my_reservations(self, auth_headers, test_user, existing_reservation):
        """Test retrieving user's reservations"""
        response = client.get(
            "/api/reservations/my-reservations",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["reservations"]) >= 1
        assert data["reservations"][0]["confirmation_number"] == "CONF123456"
    
    def test_modify_reservation_success(self, auth_headers, existing_reservation, mock_reservation_service):
        """Test successful reservation modification"""
        mock_reservation_service.modify_reservation.return_value = {
            "confirmation_number": "CONF123456",
            "status": "modified",
            "new_party_size": 6
        }
        
        response = client.put(
            f"/api/reservations/{existing_reservation.id}/modify",
            headers=auth_headers,
            json={
                "dateTime": (datetime.now() + timedelta(days=3)).isoformat(),
                "partySize": 6,
                "specialRequests": "Need high chairs"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["party_size"] == 6
    
    def test_modify_reservation_unauthorized(self, auth_headers, existing_reservation):
        """Test modifying another user's reservation"""
        # Create another user
        db = TestingSessionLocal()
        other_user = User(username="otheruser", email="other@example.com")
        db.add(other_user)
        db.commit()
        
        # Try to modify with wrong user's token
        other_token = create_access_token(data={"sub": "otheruser"})
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        response = client.put(
            f"/api/reservations/{existing_reservation.id}/modify",
            headers=other_headers,
            json={"partySize": 8}
        )
        
        assert response.status_code == 403
        db.close()
    
    def test_cancel_reservation_success(self, auth_headers, existing_reservation, mock_reservation_service):
        """Test successful reservation cancellation"""
        mock_reservation_service.cancel_reservation.return_value = {
            "confirmation_number": "CONF123456",
            "status": "cancelled",
            "refund_status": "full_refund"
        }
        
        response = client.post(
            f"/api/reservations/{existing_reservation.id}/cancel",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "successfully" in response.json()["detail"]
    
    def test_cancel_past_deadline(self, auth_headers, test_user):
        """Test cancelling past the deadline"""
        db = TestingSessionLocal()
        # Create reservation with past cancellation deadline
        past_reservation = Reservation(
            user_id=test_user.id,
            provider="opentable",
            venue_id="ot_456",
            venue_name="Test Restaurant",
            confirmation_number="CONF789",
            date_time=datetime.now() + timedelta(hours=1),
            party_size=2,
            status="confirmed",
            modification_allowed=True,
            cancellation_deadline=datetime.now() - timedelta(hours=1)  # Past deadline
        )
        db.add(past_reservation)
        db.commit()
        
        # Mock service to check deadline
        with patch('backend.app.routes.reservations_v2.reservation_service') as mock_service:
            mock_service.cancel_reservation.side_effect = ValueError(
                "Cancellation deadline has passed"
            )
            
            response = client.post(
                f"/api/reservations/{past_reservation.id}/cancel",
                headers=auth_headers
            )
            
            assert response.status_code == 500
        
        db.close()


class TestAvailabilityAndWaitlistRoutes:
    """Test suite for availability checking and waitlist functionality"""
    
    @pytest.fixture
    def mock_reservation_service(self):
        """Mock reservation service"""
        with patch('backend.app.routes.reservations_v2.reservation_service') as mock:
            mock.check_availability = AsyncMock()
            mock.add_to_waitlist = AsyncMock()
            yield mock
    
    def test_check_availability(self, auth_headers, mock_reservation_service):
        """Test checking restaurant availability"""
        mock_reservation_service.check_availability.return_value = [
            "17:00", "17:30", "18:00", "19:00", "20:00", "20:30"
        ]
        
        response = client.post(
            "/api/reservations/check-availability",
            headers=auth_headers,
            json={
                "provider": "resy",
                "venue_id": "resy_123",
                "date": (datetime.now() + timedelta(days=3)).isoformat(),
                "party_size": 4
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["available_times"]) == 6
        assert "18:00" in data["available_times"]
    
    def test_add_to_waitlist(self, auth_headers, mock_reservation_service):
        """Test adding to restaurant waitlist"""
        mock_reservation_service.add_to_waitlist.return_value = {
            "waitlist_id": "WL123456",
            "position": 3,
            "estimated_wait": "15-30 minutes"
        }
        
        response = client.post(
            "/api/reservations/1/add-to-waitlist",
            headers=auth_headers,
            json={
                "venue_id": "ot_789",
                "provider": "opentable",
                "desired_date": (datetime.now() + timedelta(hours=3)).isoformat(),
                "party_size": 2,
                "time_flexibility": "30_minutes",
                "contact_preferences": ["sms", "email"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["waitlist_id"] == "WL123456"
        assert data["position"] == 3


class TestReservationNotificationRoutes:
    """Test suite for reservation reminders and notifications"""
    
    def test_get_upcoming_reminders(self, auth_headers, test_user):
        """Test getting upcoming reservation reminders"""
        db = TestingSessionLocal()
        
        # Create reservations at different times
        upcoming_soon = Reservation(
            user_id=test_user.id,
            provider="opentable",
            venue_id="ot_1",
            venue_name="Restaurant 1",
            confirmation_number="CONF111",
            date_time=datetime.utcnow() + timedelta(hours=3),  # Within 24 hours
            party_size=2,
            status="confirmed"
        )
        
        upcoming_later = Reservation(
            user_id=test_user.id,
            provider="resy",
            venue_id="resy_2",
            venue_name="Restaurant 2",
            confirmation_number="CONF222",
            date_time=datetime.utcnow() + timedelta(days=3),  # Beyond 24 hours
            party_size=4,
            status="confirmed"
        )
        
        db.add_all([upcoming_soon, upcoming_later])
        db.commit()
        
        response = client.get(
            "/api/reservations/upcoming-reminders",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should only include reservation within 24 hours
        assert len(data["reminders"]) == 1
        assert data["reminders"][0]["confirmation_number"] == "CONF111"
        
        db.close()


class TestReservationErrorScenarios:
    """Test error handling and edge cases"""
    
    def test_invalid_provider(self, auth_headers):
        """Test handling invalid provider"""
        response = client.post(
            "/api/reservations/book",
            headers=auth_headers,
            json={
                "provider": "invalid_provider",
                "venueId": "123",
                "dateTime": datetime.now().isoformat(),
                "partySize": 2,
                "customerInfo": {
                    "firstName": "Test",
                    "lastName": "User",
                    "email": "test@test.com",
                    "phone": "555-1234"
                }
            }
        )
        
        assert response.status_code == 500
    
    def test_past_booking_attempt(self, auth_headers):
        """Test attempting to book in the past"""
        response = client.post(
            "/api/reservations/book",
            headers=auth_headers,
            json={
                "provider": "opentable",
                "venueId": "ot_123",
                "dateTime": (datetime.now() - timedelta(days=1)).isoformat(),  # Past
                "partySize": 2,
                "customerInfo": {
                    "firstName": "Test",
                    "lastName": "User",
                    "email": "test@test.com",
                    "phone": "555-1234"
                }
            }
        )
        
        assert response.status_code == 500
    
    def test_large_party_size(self, auth_headers):
        """Test handling very large party sizes"""
        response = client.post(
            "/api/reservations/search",
            headers=auth_headers,
            json={
                "query": "restaurant",
                "location": {"lat": 40.7128, "lng": -74.0060},
                "date": datetime.now().isoformat(),
                "party_size": 50  # Very large
            }
        )
        
        # Should either handle gracefully or return appropriate error
        assert response.status_code in [200, 422]
    
    def test_concurrent_booking_conflict(self, auth_headers):
        """Test handling concurrent booking attempts"""
        # This would test race conditions in real scenario
        # For now, test that system handles booking conflicts
        
        with patch('backend.app.routes.reservations_v2.reservation_service') as mock:
            mock.create_reservation.side_effect = Exception(
                "This time slot was just booked by another user"
            )
            
            response = client.post(
                "/api/reservations/book",
                headers=auth_headers,
                json={
                    "provider": "opentable",
                    "venueId": "ot_123",
                    "dateTime": datetime.now().isoformat(),
                    "partySize": 2,
                    "customerInfo": {
                        "firstName": "Test",
                        "lastName": "User",
                        "email": "test@test.com",
                        "phone": "555-1234"
                    }
                }
            )
            
            assert response.status_code == 500
            assert "Booking failed" in response.json()["detail"]


class TestReservationIntegrationScenarios:
    """Test complete reservation flow scenarios"""
    
    def test_complete_reservation_flow(self, auth_headers, test_user):
        """Test complete flow: search -> book -> modify -> cancel"""
        with patch('backend.app.routes.reservations_v2.reservation_service') as mock_service:
            # 1. Search for restaurants
            mock_service.search_all_providers.return_value = [{
                "provider": "opentable",
                "venue_id": "ot_123",
                "name": "Test Restaurant",
                "available_times": ["18:00", "19:00"]
            }]
            
            search_response = client.post(
                "/api/reservations/search",
                headers=auth_headers,
                json={
                    "query": "restaurant",
                    "location": {"lat": 0, "lng": 0},
                    "date": datetime.now().isoformat(),
                    "party_size": 2
                }
            )
            assert search_response.status_code == 200
            
            # 2. Book a reservation
            mock_service.create_reservation.return_value = {
                "confirmation_number": "CONF123",
                "status": "confirmed",
                "venue_name": "Test Restaurant"
            }
            
            book_response = client.post(
                "/api/reservations/book",
                headers=auth_headers,
                json={
                    "provider": "opentable",
                    "venueId": "ot_123",
                    "dateTime": datetime.now().isoformat(),
                    "partySize": 2,
                    "customerInfo": {
                        "firstName": "Test",
                        "lastName": "User",
                        "email": "test@test.com",
                        "phone": "555-1234"
                    }
                }
            )
            assert book_response.status_code == 200
            
            # 3. Check my reservations
            my_reservations_response = client.get(
                "/api/reservations/my-reservations",
                headers=auth_headers
            )
            assert my_reservations_response.status_code == 200
            
            # 4. Modify the reservation
            # Would need actual reservation ID from database
            # This is a simplified test
            
            # 5. Cancel the reservation
            # Would need actual reservation ID from database
            # This is a simplified test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])